<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Log;
use App\Http\Resources\LogResource;
use Illuminate\Http\Request;
class LogController extends Controller
{
    
    // public function index()
    // {
    //     $query = Log::query();

    // if (request('severity')) {
    //     $query->where('severity', request('severity'));
    // }

    // if (request('type')) {
    //     $query->where('type', request('type'));
    // }

    // if (request('from')) {
    // $query->where('timestamp', '>=', request('from'));
    // }

    // if (request('to')) {
    // $query->where('timestamp', '<=', request('to'));
    // }

    // return LogResource::collection(
    //     $query->latest('timestamp')->paginate(50)
    // );
    // }


public function index(Request $request)
{
    $query = \App\Models\Log::query();

    if ($request->filled('machine_id')) {
        $query->where('machine_id', $request->machine_id);
    }

    // filter by severity
    if ($request->filled('severity')) {
        $query->where('severity', $request->severity);
    }

    // filter by type
    if ($request->filled('type')) {
        $query->where('type', $request->type);
    }

    // date range
    if ($request->filled('from')) {
        $query->where('timestamp', '>=', $request->from);
    }

    if ($request->filled('to')) {
        $query->where('timestamp', '<=', $request->to);
    }

    if ($request->filled('machine_id_in_metadata')) {
        $query->where('metadata->machine_id', $request->machine_id_in_metadata);
    }

    return $query->orderBy('timestamp', 'desc')->paginate(50);
}
}