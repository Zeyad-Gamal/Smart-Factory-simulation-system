<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use App\Models\Machine;
use App\Models\Sensor;
class SensorSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run()
{
    $machines = Machine::all();

    foreach ($machines as $machine) {

        $sensors = [
            ['type' => 'pressure', 'name' => 'PT1'],
            ['type' => 'pressure', 'name' => 'PT2'],
            ['type' => 'pressure', 'name' => 'PT3'],
            ['type' => 'pressure', 'name' => 'PT4'],

            ['type' => 'motor', 'name' => 'rpm'],
            ['type' => 'motor', 'name' => 'load'],

            ['type' => 'vibration', 'name' => 'vibration'],

            ['type' => 'output', 'name' => 'rate'],
            ['type' => 'output', 'name' => 'total'],

            ['type' => 'level', 'name' => 'hopper'],
            ['type' => 'level', 'name' => 'buffer'],
        ];

        foreach ($sensors as $sensor) {
            Sensor::create([
                'machine_id' => $machine->id,
                'type' => $sensor['type'],
                'name' => $sensor['name'],
                'value' => 0
            ]);
        }
    }
}
}
