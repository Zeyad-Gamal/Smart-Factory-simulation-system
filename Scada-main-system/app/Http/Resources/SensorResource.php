<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class SensorResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @return array<string, mixed>
     */
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'machine_id' => $this->machine_id,
            'type' => $this->type,
            'value' => $this->value,
            'updated_at' => $this->updated_at,
        ];
    }
}
