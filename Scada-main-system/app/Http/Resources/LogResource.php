<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class LogResource extends JsonResource
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

            'type' => $this->type,
            'message' => $this->message,
            'severity' => $this->severity,

            'timestamp' => $this->timestamp,

            
            'machine_id' => $this->metadata['machine_id'] ?? null,
            'sensor_id' => $this->metadata['sensor_id'] ?? null,
            'value' => $this->metadata['value'] ?? null,

            
            'metadata' => $this->metadata,
        ];
    }
}
