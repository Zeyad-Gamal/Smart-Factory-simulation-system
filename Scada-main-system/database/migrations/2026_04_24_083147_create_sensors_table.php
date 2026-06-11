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
        Schema::create('sensors', function (Blueprint $table) {
    $table->id();
    $table->foreignId('machine_id')->constrained()->cascadeOnDelete();

    $table->string('type');   // pressure, motor, level
    $table->string('name');   // PT1, PT2, rpm, load...

    $table->float('value')->default(0);

    $table->timestamps();
});
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('sensors');
    }
};
