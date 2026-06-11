<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('soc_alerts', function (Blueprint $table) {
            

            $table->id();
 
            // ── SOC Decision fields ──────────────────────────────
            $table->string('decision_id')->unique();
            $table->string('log_id')->nullable();
            $table->string('threat_type');
            $table->string('severity');          // critical | high | medium | low | info
            $table->unsignedTinyInteger('confidence')->default(0); // 0-100
            $table->text('decision');
            $table->text('reasoning');
            $table->string('status');            // approved | rejected | pending
            $table->text('operator_note')->nullable();
 
            // ── SCADA context (extracted from extra{}) ───────────
            $table->unsignedBigInteger('machine_id')->nullable();
            $table->string('machine_name')->nullable();
            $table->string('sensor_name')->nullable();
            $table->string('sensor_type')->nullable();
            $table->float('sensor_value')->nullable();
 
            // ── SOC timestamps ───────────────────────────────────
            $table->timestamp('soc_created_at')->nullable();
            $table->timestamp('soc_resolved_at')->nullable();
 
            // ── Laravel timestamps ───────────────────────────────
            $table->timestamps();
 
            // ── Indexes ──────────────────────────────────────────
            $table->index('severity');
            $table->index('status');
            $table->index('machine_id');
            $table->index('soc_created_at');

        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('soc_alerts');
    }
};
