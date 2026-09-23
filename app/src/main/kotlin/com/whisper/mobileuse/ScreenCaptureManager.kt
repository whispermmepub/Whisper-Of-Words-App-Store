package com.whisper.mobileuse

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager

object ScreenCaptureManager {
    const val REQUEST_CODE = 401
    var projection: MediaProjection? = null

    fun request(activity: Activity) {
        val manager = activity.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        activity.startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_CODE)
    }

    fun acceptResult(activity: Activity, resultCode: Int, data: Intent?): Boolean {
        if (resultCode != Activity.RESULT_OK || data == null) return false
        val manager = activity.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        projection = manager.getMediaProjection(resultCode, data)
        return projection != null
    }

    fun stop() {
        projection?.stop()
        projection = null
    }
}
