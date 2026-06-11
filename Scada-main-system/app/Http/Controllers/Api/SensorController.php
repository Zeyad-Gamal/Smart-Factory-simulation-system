<?php

namespace App\Http\Controllers\api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Http\Resources\SensorResource;
use App\Models\Sensor;
class SensorController extends Controller
{
    public function index()
    {
        $query = Sensor::query();


        if (request()->has('machine_id')) {
            $query->where('machine_id', request('machine_id'));
        }

        if (request()->has('type')) {
            $query->where('type', request('type'));
        }

        return SensorResource::collection(
    Sensor::query()
        ->orderByDesc('updated_at')
        ->limit(200)
        ->get()
);
    }

    public function show($id)
    {
        $sensor = Sensor::findOrFail($id);

        return new SensorResource($sensor);
    }
}
