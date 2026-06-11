<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Sensor extends Model
{
    protected $fillable = ['machine_id', 'type', 'name', 'value' ,'element_no'];

    public function machine()
    {
        return $this->belongsTo(Machine::class);
    }
}
