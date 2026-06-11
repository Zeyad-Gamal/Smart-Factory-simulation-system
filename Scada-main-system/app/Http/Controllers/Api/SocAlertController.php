<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\SocAlert;
use Illuminate\Http\Request;

class SocAlertController extends Controller
{
    // ════════════════════════════════════════════════════════
    //  POST /api/soc/webhook
    //  Called by the SOC after operator approves or rejects.
    //  Stores the decision in the DB.
    // ════════════════════════════════════════════════════════
    public function webhook(Request $request)
    {
        $data = $request->validate([
            'decision_id'   => 'required|string',
            'log_id'        => 'nullable|string',
            'threat_type'   => 'required|string',
            'severity'      => 'required|string',
            'confidence'    => 'nullable|integer',
            'decision'      => 'required|string',
            'reasoning'     => 'nullable|string',
            'status'        => 'required|string',
            'operator_note' => 'nullable|string',
            'created'       => 'nullable|string',
            'resolved'      => 'nullable|string',
            'extra'         => 'nullable|array',
        ]);

        // Extract SCADA context from extra{}
        $extra = $data['extra'] ?? [];

        // Upsert — if SOC sends the same decision twice, update it
        $alert = SocAlert::updateOrCreate(
            ['decision_id' => $data['decision_id']],
            [
                'log_id'          => $data['log_id']        ?? null,
                'threat_type'     => $data['threat_type'],
                'severity'        => strtolower($data['severity']),
                'confidence'      => $data['confidence']    ?? 0,
                'decision'        => $data['decision'],
                'reasoning'       => $data['reasoning']     ?? '',
                'status'          => strtolower($data['status']),
                'operator_note'   => $data['operator_note'] ?? null,
                'machine_id'      => $extra['machine_id']   ?? null,
                'machine_name'    => $extra['machine_name'] ?? null,
                'sensor_name'     => $extra['sensor_name']  ?? null,
                'sensor_type'     => $extra['sensor_type']  ?? null,
                'sensor_value'    => $extra['value']        ?? null,
                'soc_created_at'  => $data['created']       ?? null,
                'soc_resolved_at' => $data['resolved']      ?? null,
            ]
        );

        // Log the received alert
        app(LogService::class)->log(
            type: 'soc_alert_received',
            message: "SOC alert received: {$data['threat_type']} — {$data['status']}",
            severity: $data['severity'],
            metadata: [
                'decision_id' => $data['decision_id'],
                'machine_id'  => $extra['machine_id'] ?? null,
                'status'      => $data['status'],
            ]
        );

        return response()->json([
            'status' => 'ok',
            'id'     => $alert->id,
        ]);
    }

    // ════════════════════════════════════════════════════════
    //  GET /api/soc/alerts
    //  Returns all stored SOC alerts — used by the Vue page.
    //  Query params:
    //    severity   : filter by severity
    //    status     : filter by status
    //    machine_id : filter by machine
    //    limit      : max records (default 100)
    // ════════════════════════════════════════════════════════
    public function index(Request $request)
    {
        $query = SocAlert::query()->orderByDesc('soc_created_at');

        if ($request->filled('severity')) {
            $query->where('severity', strtolower($request->severity));
        }

        if ($request->filled('status')) {
            $query->where('status', strtolower($request->status));
        }

        if ($request->filled('machine_id')) {
            $query->where('machine_id', $request->machine_id);
        }

        $limit  = (int) $request->get('limit', 100);
        $alerts = $query->limit($limit)->get();

        return response()->json([
            'status' => 'ok',
            'count'  => $alerts->count(),
            'data'   => $alerts,
        ]);
    }

    // ════════════════════════════════════════════════════════
    //  GET /api/soc/alerts/stats
    //  Returns summary stats for the SCADA dashboard KPIs.
    // ════════════════════════════════════════════════════════
    public function stats()
    {
        return response()->json([
            'status' => 'ok',
            'data'   => [
                'total'    => SocAlert::count(),
                'critical' => SocAlert::critical()->count(),
                'approved' => SocAlert::approved()->count(),
                'rejected' => SocAlert::rejected()->count(),
                'pending'  => SocAlert::pending()->count(),
            ],
        ]);
    }
}