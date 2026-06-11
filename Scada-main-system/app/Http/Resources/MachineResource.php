<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class MachineResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @return array<string, mixed>
     */
    
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'status' => $this->status,
            'last_started_at' => $this->last_started_at,

            
            'sensors' => $this->formatSensors(),
        ];
    }

    private function formatSensors()
    {
        $data = [];

        foreach ($this->sensors as $sensor) {
            $data[$sensor->type] = $sensor->value;
        }

        return $data;
    }
}
