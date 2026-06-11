<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Log extends Model
{
    public $timestamps = false;

    protected $fillable = [
        'type',
        'message',
        'severity',
        'metadata',
        'timestamp'
    ];

    protected $casts = [
        'metadata' => 'array',
        'timestamp' => 'datetime'
    ];
}
