// set_caps_led: 直接控制键盘 Caps Lock LED（不经过大写状态）
// 用法: set_caps_led on|off
// 原理: IOKit HID —— 找键盘设备的 LED 元件(CapsLock)并写入
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/hid/IOHIDManager.h>
#include <stdio.h>
#include <string.h>

static int g_on = 0;
static int g_set = 0;
static int g_devs = 0, g_leds = 0;

static void setDeviceLed(IOHIDDeviceRef dev) {
    g_devs++;
    CFArrayRef elems = IOHIDDeviceCopyMatchingElements(dev, NULL, kIOHIDOptionsTypeNone);
    if (!elems) return;
    CFIndex n = CFArrayGetCount(elems);
    for (CFIndex i = 0; i < n; i++) {
        IOHIDElementRef e = (IOHIDElementRef)CFArrayGetValueAtIndex(elems, i);
        if (IOHIDElementGetUsagePage(e) == kHIDPage_LEDs &&
            IOHIDElementGetUsage(e) == kHIDUsage_LED_CapsLock) {
            g_leds++;
            IOHIDValueRef v = IOHIDValueCreateWithIntegerValue(kCFAllocatorDefault, e, 0, g_on ? 1 : 0);
            if (v) {
                IOReturn r = IOHIDDeviceSetValue(dev, e, v);
                if (r == kIOReturnSuccess) g_set++;
                else fprintf(stderr, "device %p led write: 0x%x\n", (void*)dev, r);
                CFRelease(v);
            }
        }
    }
    CFRelease(elems);
}

int main(int argc, char **argv) {
    if (argc < 2 || (strcmp(argv[1], "on") && strcmp(argv[1], "off"))) {
        fprintf(stderr, "usage: %s on|off\n", argv[0]);
        return 2;
    }
    g_on = !strcmp(argv[1], "on");

    IOHIDManagerRef mgr = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    if (!mgr) return 1;

    // 匹配键盘设备 (usagePage=1 GenericDesktop, usage=6 Keyboard)
    CFMutableDictionaryRef match = CFDictionaryCreateMutable(kCFAllocatorDefault, 0, NULL, NULL);
    int page = kHIDPage_GenericDesktop, usage = kHIDUsage_GD_Keyboard;
    CFDictionarySetValue(match, CFSTR(kIOHIDDeviceUsagePageKey), CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &page));
    CFDictionarySetValue(match, CFSTR(kIOHIDDeviceUsageKey), CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &usage));
    IOHIDManagerSetDeviceMatching(mgr, match);
    CFRelease(match);

    CFSetRef devs = IOHIDManagerCopyDevices(mgr);
    if (devs) {
        CFIndex n = CFSetGetCount(devs);
        IOHIDDeviceRef *buf = calloc(n, sizeof(IOHIDDeviceRef));
        CFSetGetValues(devs, (const void **)buf);
        for (CFIndex i = 0; i < n; i++) setDeviceLed(buf[i]);
        free(buf);
        CFRelease(devs);
    }
    CFRelease(mgr);
    fprintf(stderr, "devices=%d caps_led_elements=%d written=%d\n", g_devs, g_leds, g_set);
    return g_set ? 0 : 1;
}
