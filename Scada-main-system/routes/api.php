<?php

use App\Http\Controllers\Api\MachineController;
use App\Http\Controllers\Api\LogController;
use App\Http\Controllers\Api\ScadaController;
use App\Http\Controllers\SensorHistoryController;
use App\Http\Controllers\Api\ScadaActionController;
use App\Http\Controllers\Api\SocAlertController;

Route::get('/machines', [MachineController::class, 'index']);
Route::get('/machines/{id}', [MachineController::class, 'show']);

Route::middleware('throttle:10,1')->group(function () {
Route::post('/machines/{id}/start', [MachineController::class, 'start']);
Route::post('/machines/{id}/stop', [MachineController::class, 'stop']);
});

Route::get('/logs', [LogController::class, 'index']);


Route::get('/scada-data', [ScadaController::class, 'index']);



Route::get('/scada/history', [SensorHistoryController::class, 'index']);
Route::post('/scada/history', [SensorHistoryController::class, 'store']);



Route::post('/scada/action', [ScadaActionController::class, 'execute']);





Route::post('/soc/webhook',       [SocAlertController::class, 'webhook']);
Route::get('/soc/alerts',         [SocAlertController::class, 'index']);
Route::get('/soc/alerts/stats',   [SocAlertController::class, 'stats']);






Route::get('/health', function () {
    return response()->json(['status' => 'ok'], 200);
});