<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Services\ScadaActionService;

class ScadaActionController extends Controller
{
    public function execute(
        Request $request,
        ScadaActionService $service
    ) {

        $data = $request->validate([
            'action' => 'required|string',
            'machine_id' => 'required|integer',
            'reason' => 'nullable|string'
        ]);

        return response()->json(
            $service->execute(
                $data['action'],
                $data['machine_id'],
                $data['reason'] ?? null
            )
        );
    }
}