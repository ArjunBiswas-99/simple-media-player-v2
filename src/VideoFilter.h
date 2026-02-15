#ifndef VIDEOFILTER_H
#define VIDEOFILTER_H

struct VideoFilter {
    float brightness;  // -100 to +100
    float contrast;    // -100 to +100
    float saturation;  // -100 to +100
    float hue;         // -180 to +180
    
    VideoFilter() : brightness(0), contrast(0), saturation(0), hue(0) {}
};

#endif // VIDEOFILTER_H
