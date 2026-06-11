<?php

namespace App\Jobs;

use App\Models\Machine;
use App\Models\Sensor;
use App\Models\IndicatorSwitch;
use App\Models\SensorHistory;

class UpdateSensorsJob
{
    public function handle()
    {
        $machines = Machine::with([
            'sensors',
            'indicatorSwitches'
        ])->get();

        foreach ($machines as $machine) {

            $isRunning = in_array(
                strtoupper(trim($machine->status)),
                ['ON', 'RUNNING', 'ACTIVE', '1']
            );

            // ══════════════════════════════════════
            //  MACHINE OFF
            // ══════════════════════════════════════
            if (!$isRunning) {

                foreach ($machine->sensors as $sensor) {

                    // Keep total accumulating, zero everything else
                    $value = $sensor->type === 'total'
                        ? $sensor->value
                        : 0;

                    $sensor->update(['value' => $value]);
                    $sensor->value = $value;

                    SensorHistory::create([
                        'machine_id'  => $machine->id,
                        'sensor_id'   => $sensor->id,
                        'sensor_type' => $sensor->type,
                        'value'       => $value,
                        'recorded_at' => now(),
                    ]);
                }

                foreach ($machine->indicatorSwitches as $switch) {
                    if ($switch->value != 0) {
                        $switch->update(['value' => 0]);
                        $switch->value = 0;
                    }
                }

                continue;
            }

            // ══════════════════════════════════════
            //  MACHINE ON — calculate base values
            // ══════════════════════════════════════
            $rpm = rand(1450, 1850);

            $load = max(20, min(85,
                40 + (($rpm - 1450) / 400) * 30 + rand(-3, 3)
            ));

            $pressure = max(6, min(17,
                8 + ($load / 100) * 6 + rand(-1, 1)
            ));

            $vibration = max(0.5, min(7,
                1.5 + ($load / 100) * 3 + rand(0, 1)
            ));

            $rate = 90 + (($rpm - 1450) / 400) * 50 + rand(-5, 5);

            // ── Occasional anomalies (~8% total chance) ──
            $fault = rand(1, 100);

            if ($fault <= 3)
                $pressure  += rand(4, 7);   // ~3% high pressure spike

            if ($fault >= 4 && $fault <= 6)
                $vibration += rand(2, 4);   // ~3% high vibration spike

            if ($fault >= 7 && $fault <= 8)
                $load      += rand(10, 20); // ~2% motor overload

            // Clamp after anomaly injection
            $pressure  = max(0, min(25, $pressure));
            $load      = max(0, min(100, $load));
            $vibration = max(0, min(12, $vibration));

            // ══════════════════════════════════════
            //  UPDATE SENSORS
            // ══════════════════════════════════════
            foreach ($machine->sensors as $sensor) {

                switch ($sensor->type) {

                    case 'rpm':
                        $value = $rpm;
                        break;

                    case 'load':
                        $value = $load;
                        break;

                    case 'vibration':
                        $value = $vibration;
                        break;

                    case 'pressure':
                        $value = $pressure + (
                            in_array($sensor->name, ['PT1', 'PT2', 'PT3', 'PT4'])
                            ? rand(-1, 1)
                            : 0
                        );
                        break;

                    case 'rate':
                        $value = $rate;
                        break;

                    case 'total':
                        $value = $sensor->value + $rate;
                        break;

                    case 'level':
                        if (str_contains($sensor->name, 'Hopper')) {
                            $feed    = rand(1, 3);
                            $consume = $rate / 40;
                            $value   = $sensor->value + $feed - $consume;

                        } elseif (str_contains($sensor->name, 'Buffer')) {
                            $bufferFlow = ($load - 40) / 8;
                            $value      = $sensor->value + $bufferFlow;

                        } else {
                            $value = $sensor->value;
                        }

                        $value = round(max(0, min(100, $value)), 2);
                        break;

                    default:
                        app(\App\Services\LogService::class)->log(
                            type: 'unknown_sensor_detected',
                            message: "Unknown sensor: {$sensor->name}",
                            severity: 'warning',
                            metadata: [
                                'machine_id'  => $sensor->machine_id,
                                'sensor_name' => $sensor->name,
                            ]
                        );
                        $value = $sensor->value;
                }

                $sensor->update(['value' => $value]);
                $sensor->value = $value;

                // ── Anomaly detection & SOC alerts ──────────
                if ($sensor->type === 'pressure' && $value > 21) {
                    $this->logAnomaly($machine, $sensor, $value, 'High pressure');
                    $this->sendToSOC($machine, $sensor, $value, 'High pressure detected', 'critical');
                }

                if ($sensor->type === 'vibration' && $value > 9) {
                    $this->logAnomaly($machine, $sensor, $value, 'High vibration');
                    $this->sendToSOC($machine, $sensor, $value, 'High vibration detected', 'high');
                }

                if ($sensor->type === 'load' && $value > 92) {
                    $this->logAnomaly($machine, $sensor, $value, 'Motor overload');
                    $this->sendToSOC($machine, $sensor, $value, 'Motor overload detected', 'high');
                }

                if ($sensor->type === 'level'
                    && str_contains($sensor->name, 'Hopper')
                    && $value > 98
                ) {
                    $this->logAnomaly($machine, $sensor, $value, 'Hopper overflow');
                    $this->sendToSOC($machine, $sensor, $value, 'Hopper overflow detected', 'medium');
                }
                // ────────────────────────────────────────────

                SensorHistory::create([
                    'machine_id'  => $machine->id,
                    'sensor_id'   => $sensor->id,
                    'sensor_type' => $sensor->type,
                    'value'       => $value,
                    'recorded_at' => now(),
                ]);
            }

            $this->updateIndicators($machine, $machines);
        }
    }

    // ══════════════════════════════════════════════
    //  INDICATORS
    // ══════════════════════════════════════════════

    private function updateIndicators($machine, $machines = null)
    {
        $isRunning = in_array(
            strtoupper(trim($machine->status)),
            ['ON', 'RUNNING', 'ACTIVE', '1']
        );

        $state = $isRunning ? $this->buildState($machine) : [];

        foreach ($machine->indicatorSwitches as $switch) {

            $value = $isRunning
                ? (int) $this->evaluateIndicator($switch, $state, $machines, $machine)
                : 0;

            if ((int) $switch->value === $value) continue;

            $switch->update(['value' => $value]);
            $switch->value = $value;
        }
    }

    private function buildState($machine)
    {
        return [
            'rpm'       => $machine->sensors->firstWhere('type', 'rpm')?->value       ?? 0,
            'vibration' => $machine->sensors->firstWhere('type', 'vibration')?->value ?? 0,
            'load'      => $machine->sensors->firstWhere('type', 'load')?->value      ?? 0,
            'pressure'  => $machine->sensors->where('type', 'pressure')->avg('value') ?? 0,
            'running'   => in_array(strtoupper($machine->status), ['ON', 'RUNNING', 'ACTIVE', '1']),
        ];
    }

    private function evaluateIndicator($switch, $state, $machines = null, $machine = null)
    {
        $name = $switch->name;

        // Motors → ON if rpm > 0
        if (str_contains($name, 'Motor')) {
            return $state['rpm'] > 0 ? 1 : 0;
        }

        // Cooling Pump → ON if vibration high
        if ($name === 'Cooling Pump') {

    return (
        $state['running']
        &&
        $state['pressure'] > 10
    )
    ? 1
    : 0;
}

        // Conveyors → ON if machine running
        if (
    str_contains($name,'Conveyor')
    ||
    str_starts_with($name,'CV')
) {
    return $state['running']
        && $state['rpm'] > 0
        ? 1
        : 0;
}

        // Hopper indicators → based on load
        if (str_contains($name, 'Hopper')) {
            return $state['load'] > 50 ? 1 : 0;
        }

        // Buffer indicators → based on Buffer Level sensor value
        if (str_contains($name, 'Buffer')) {
            if (!$machine) return (int) $switch->value;

            $bufferLevel = $machine->sensors
                ->filter(fn($s) => $s->type === 'level' && str_contains($s->name, 'Buffer'))
                ->first()?->value ?? 0;

            if (str_contains($name, 'HH')) return $bufferLevel > 90 ? 1 : 0;
            if (str_contains($name, 'H'))  return $bufferLevel > 70 ? 1 : 0;
            if (str_contains($name, 'M'))  return $bufferLevel > 50 ? 1 : 0;
            if (str_contains($name, 'L'))  return $bufferLevel < 20 ? 1 : 0;

            return 0;
        }

        // Dosing → ON if machine running
        if (str_contains($name, 'Dosing')) {
            return $state['running'] ? 1 : 0;
        }

        return (int) $switch->value;
    }

    // ══════════════════════════════════════════════
    //  HELPERS
    // ══════════════════════════════════════════════

    private function logAnomaly($machine, $sensor, $value, $message)
    {
        app(\App\Services\LogService::class)->log(
            type: 'anomaly_detected',
            message: $message,
            severity: 'critical',
            metadata: [
                'machine_id' => $machine->id,
                'sensor'     => $sensor->name,
                'value'      => $value,
            ]
        );
    }

    private function sendToSOC($machine, $sensor, $value, $anomalyMessage, $severity = 'high')
    {
        $socUrl = env('SOC_URL', 'http://localhost:5000');

        $payload = [
            'source'   => 'scada-laravel',
            'severity' => $severity,
            'message'  => $anomalyMessage,
            'raw'      => [
                'machine_id'   => $machine->id,
                'machine_name' => $machine->name,
                'sensor_name'  => $sensor->name,
                'sensor_type'  => $sensor->type,
                'value'        => $value,
                'timestamp'    => now()->toISOString(),
            ],
        ];

        try {
            \Illuminate\Support\Facades\Http::timeout(3)
                ->post("{$socUrl}/api/ingest", $payload);
        } catch (\Exception $e) {
            logger()->warning('SOC ingest failed: ' . $e->getMessage());
        }
    }
}