<?php

namespace App\Http\Controllers;

use App\Models\SensorHistory;
use Illuminate\Http\Request;

class SensorHistoryController extends Controller
{
    /**
     * Get history data for SCADA charts
     */
    public function index(Request $request)
{
    $query = SensorHistory::query();

    if ($request->machine_id) {
        $query->where('machine_id', $request->machine_id);
    }

    if ($request->sensor_type) {
        $query->where('sensor_type', $request->sensor_type);
    }

    if ($request->date) {
        $query->whereDate('recorded_at', $request->date);
    }

    $data = $query->orderBy('recorded_at')->get();

    return response()->json(
        $data->map(function ($item) {
            return [
                'name' => $item->sensor_type,
                'time' => $item->recorded_at->format('H:i'),
                'value' => $item->value,
            ];
        })
    );
}

    /**
     * Store new sensor reading (from simulation / real system)
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'machine_id' => 'required|integer',
            'sensor_id' => 'nullable|integer',
            'sensor_type' => 'required|string',
            'value' => 'required|numeric',
            'recorded_at' => 'nullable|date',
            'meta' => 'nullable|array',
        ]);

        $history = SensorHistory::create([
            'machine_id' => $validated['machine_id'],
            'sensor_id' => $validated['sensor_id'] ?? null,
            'sensor_type' => $validated['sensor_type'],
            'value' => $validated['value'],
            'recorded_at' => $validated['recorded_at'] ?? now(),
            'meta' => $validated['meta'] ?? null,
        ]);

        return response()->json([
            'message' => 'Recorded successfully',
            'data' => $history
        ]);
    }
}