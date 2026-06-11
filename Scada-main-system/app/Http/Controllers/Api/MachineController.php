<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Machine;
use App\Services\MachineService;
use App\Http\Resources\MachineResource;
use Illuminate\Http\Request;

class MachineController extends Controller
{
    public function index()
    {
        $machines = Machine::with('sensors')->get();
        return MachineResource::collection($machines);
    }

    public function show($id)
    {
        $machine = Machine::with('sensors')->findOrFail($id);
        return new MachineResource($machine);
    }

    public function start($id, MachineService $service)
    {
        $machine = Machine::findOrFail($id);
        $updated = $service->start($machine);
        return new MachineResource($updated->load('sensors'));
    }

    public function stop($id, MachineService $service)
    {
        $machine = Machine::findOrFail($id);
        $updated = $service->stop($machine);
        return new MachineResource($updated->load('sensors'));
    }
}