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


        Schema::create('sensor_histories', function (Blueprint $table) {
            $table->id();

            $table->unsignedBigInteger('machine_id');
            $table->unsignedBigInteger('sensor_id')->nullable();

            $table->string('sensor_type'); // temperature, rpm, vibration...

            $table->float('value');

            $table->timestamp('recorded_at')->useCurrent();

            $table->json('meta')->nullable();

            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('sensor_histories');
    }
};
