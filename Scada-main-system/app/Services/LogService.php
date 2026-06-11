<?php

namespace App\Services;

use App\Models\Log;

class LogService
{

public function log($type, $message, $severity = 'info', $metadata = [])
{
    $logData = [
        'type' => $type,
        'message' => $message,
        'severity' => $severity,
        'timestamp' => now()->toDateTimeString(),

        // flatten important fields
        'machine_id' => $metadata['machine_id'] ?? null,
        'sensor_id' => $metadata['sensor_id'] ?? null,
        'value' => $metadata['value'] ?? null,

        // keep full metadata too
        'metadata' => $metadata,
    ];

    // save in DB
    $log = Log::create($logData);

    // write to file (ده اللي هيستخدمه SOC)
    file_put_contents(
        storage_path('logs/soc.log'),
        json_encode($logData) . PHP_EOL,
        FILE_APPEND
    );

    return $log;
}
}