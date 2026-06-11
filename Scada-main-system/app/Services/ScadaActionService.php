<?php

namespace App\Services;

use App\Models\Machine;

class ScadaActionService
{
    public function execute(
        string $action,
        int $machineId,
        ?string $reason
    ) {

        $machine = Machine::findOrFail($machineId);

        switch ($action) {

            case 'shutdown_machine':

                $machine->update([
                    'status' => 'OFF'
                ]);

                break;

            case 'alert_maintenance':

                app(LogService::class)->log(
                    type: 'maintenance_alert',
                    message: $reason,
                    severity: 'warning',
                    metadata: [
                        'machine_id'=>$machineId
                    ]
                );

                break;

            case 'isolate_machine':

                $machine->update([
                    'status'=>'ISOLATED'
                ]);

                break;

            default:

                abort(400,'Unknown action');
        }

        app(LogService::class)->log(
            type:'soc_action',
            message:$action,
            severity:'critical',
            metadata:[
                'machine_id'=>$machineId,
                'reason'=>$reason
            ]
        );

        return [
            'success'=>true,
            'machine'=>$machineId,
            'action'=>$action
        ];
    }
}