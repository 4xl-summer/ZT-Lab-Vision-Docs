#include "zvision.h"
#include <stdint.h>
#include <stdio.h>

int main(void) {
    const uint8_t pixels[] = {0, 127, 128, 255};
    uint8_t output[4] = {0};
    uint64_t image = 0, mask = 0;
    int32_t status = ZV_OK;
    int exit_code = 1;
    if (zv_abi_version() != ZV_ABI_VERSION) {
        fprintf(stderr, "ABI mismatch\n");
        return 1;
    }
    status = zv_image_create_gray8(2, 2, pixels, 4, &image);
    if (status != ZV_OK) goto cleanup;
    status = zv_image_threshold_gray8(image, 128, &mask);
    if (status != ZV_OK) goto cleanup;
    status = zv_image_copy_gray8(mask, output, 4);
    if (status != ZV_OK) goto cleanup;
    if (output[0] != 0 || output[1] != 0 || output[2] != 255 || output[3] != 255) {
        fprintf(stderr, "unexpected pixels\n");
        goto cleanup;
    }
    printf("%u %u %u %u\n", (unsigned)output[0], (unsigned)output[1],
           (unsigned)output[2], (unsigned)output[3]);
    exit_code = 0;
cleanup:
    if (status != ZV_OK) fprintf(stderr, "ZVision status: %d\n", (int)status);
    if (mask && zv_handle_release(mask) != ZV_OK) exit_code = 1;
    if (image && zv_handle_release(image) != ZV_OK) exit_code = 1;
    return exit_code;
}
