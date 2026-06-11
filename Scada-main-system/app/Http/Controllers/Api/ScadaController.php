<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Sensor;
use App\Models\IndicatorSwitch;

class ScadaController extends Controller
{
    

// public function index()
// {
//     return \App\Models\Machine::with('sensors')
//         ->get()
//         ->mapWithKeys(function ($machine) {
//             return [
//                 $machine->name => $machine->sensors
//                     ->pluck('value', 'name')
//             ];
//         });
// }





public function index()
{
    
    $now = now();

    $latest_data = Sensor::all()->map(function ($sensor) use ($now) {
        return [
            'element_no' => (string) $sensor->element_no,
            'name' => $sensor->name,
            'value' => (string) $sensor->value,
            'type' => $sensor->type,

            'year' => $now->format('Y'),
            'month' => $now->format('m'),
            'day' => $now->format('d'),
            'hour' => $now->format('H'),
            'min' => $now->format('i'),
        ];
    });

    $check_data = IndicatorSwitch::all()->map(function ($sw) {
        return [
            'element_no' => (string) $sw->element_no,
            'name' => $sw->name,
            'value' => $sw->value ? '1' : '0',
        ];
    });

    return response()->json([
        'latest_data' => $latest_data,
        'check_data' => $check_data,
    ]);
}
}
