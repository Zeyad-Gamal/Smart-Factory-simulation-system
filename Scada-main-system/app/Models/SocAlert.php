<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SocAlert extends Model
{
    protected $fillable = [
        'decision_id',
        'log_id',
        'threat_type',
        'severity',
        'confidence',
        'decision',
        'reasoning',
        'status',
        'operator_note',
        'machine_id',
        'machine_name',
        'sensor_name',
        'sensor_type',
        'sensor_value',
        'soc_created_at',
        'soc_resolved_at',
    ];

    protected $casts = [
        'confidence'      => 'integer',
        'machine_id'      => 'integer',
        'sensor_value'    => 'float',
        'soc_created_at'  => 'datetime',
        'soc_resolved_at' => 'datetime',
    ];

    // ── Scopes ────────────────────────────────────────────────

    public function scopeCritical($query)
    {
        return $query->where('severity', 'critical');
    }

    public function scopeApproved($query)
    {
        return $query->where('status', 'approved');
    }

    public function scopeRejected($query)
    {
        return $query->where('status', 'rejected');
    }

    public function scopePending($query)
    {
        return $query->where('status', 'pending');
    }

    public function scopeForMachine($query, int $machineId)
    {
        return $query->where('machine_id', $machineId);
    }
}