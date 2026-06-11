<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;
use App\Jobs\UpdateSensorsJob;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');



// Schedule::job(UpdateSensorsJob::class)->everyMinute();


Schedule::call(function () {
    dispatch(new \App\Jobs\UpdateSensorsJob());
})->everyMinute();
