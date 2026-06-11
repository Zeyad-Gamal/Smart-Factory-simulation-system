<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Machine extends Model
{
    protected $fillable = ['name', 'status', 'last_started_at'];

    public function sensors()
    {
        return $this->hasMany(Sensor::class);
    }

    public function indicatorSwitches()
{
    return $this->hasMany(IndicatorSwitch::class);
}
}
