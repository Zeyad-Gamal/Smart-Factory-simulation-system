<?php

namespace App\Services;

use App\Models\Machine;
use App\Services\LogService;
use Carbon\Carbon;
use Exception;

class MachineService
{
    public function start(Machine $machine)
    {
        if ($machine->status === 'ON') {
            throw new Exception('Machine already ON');
        }

        $machine->update([
            'status' => 'ON',
            'last_started_at' => Carbon::now()
        ]);

        app(LogService::class)->log(
            type: 'machine_started',
            message: "Machine {$machine->name} started",
            severity: 'info',
            metadata: ['machine_id' => $machine->id]
        );

        return $machine;
    }

    public function stop(Machine $machine)
    {
        if ($machine->status === 'OFF') {
            throw new Exception('Machine already OFF');
        }

        $machine->update([
            'status' => 'OFF'
        ]);

        app(LogService::class)->log(
            type: 'machine_stopped',
            message: "Machine {$machine->name} stopped",
            severity: 'warning',
            metadata: ['machine_id' => $machine->id]
        );

        return $machine;
    }
}