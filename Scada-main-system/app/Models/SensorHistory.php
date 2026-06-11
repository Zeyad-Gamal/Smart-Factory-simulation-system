<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SensorHistory extends Model
{
    protected $table = 'sensor_histories';

    protected $fillable = [
        'machine_id',
        'sensor_id',
        'sensor_type',
        'value',
        'recorded_at',
        'meta',
    ];

    protected $casts = [
        'meta' => 'array',
        'recorded_at' => 'datetime',
        'value' => 'float',
    ];
}