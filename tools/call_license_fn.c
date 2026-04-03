#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*about_fn_t)(
    int,
    char *,
    char *,
    char *,
    char *,
    char *,
    char *,
    char *
);

typedef int (*check_fn_t)(int, int, const char *);
typedef int (*decode_fn_t)(char *, char *, char *);
typedef int (*int_field_fn_t)(char *, int);
typedef void (*str_field_fn_t)(char *, char *, int, int);

int main(int argc, char **argv) {
    const char *libpath =
        argc > 1 ? argv[1] : "/home/epictus/ctf/stata18-toolkit/runtime/stata-local/libstata.so";

    void *handle = dlopen(libpath, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    void *sym = dlsym(handle, "StataSO_Main");
    if (!sym) {
        fprintf(stderr, "dlsym failed: %s\n", dlerror());
        return 1;
    }

    Dl_info info;
    if (!dladdr(sym, &info) || !info.dli_fbase) {
        fprintf(stderr, "dladdr failed\n");
        return 1;
    }

    about_fn_t about_fn = (about_fn_t)((char *)info.dli_fbase + 0x9a5991);
    check_fn_t check_fn = (check_fn_t)((char *)info.dli_fbase + 0x9a5e88);
    decode_fn_t decode_fn = (decode_fn_t)((char *)info.dli_fbase + 0x5eb151);
    int_field_fn_t int_field_fn = (int_field_fn_t)((char *)info.dli_fbase + 0x9a586a);
    str_field_fn_t str_field_fn = (str_field_fn_t)((char *)info.dli_fbase + 0x9d77b8);

    char a[4096];
    char b[4096];
    char c[4096];
    char d[4096];
    char e[4096];
    char f[4096];
    char g[4096];
    memset(a, 0, sizeof(a));
    memset(b, 0, sizeof(b));
    memset(c, 0, sizeof(c));
    memset(d, 0, sizeof(d));
    memset(e, 0, sizeof(e));
    memset(f, 0, sizeof(f));
    memset(g, 0, sizeof(g));

    int check_rc = check_fn(1, 0, NULL);
    int about_rc = about_fn(1, a, b, c, d, e, f, g);

    printf("check_rc=%d\n", check_rc);
    printf("about_rc=%d\n", about_rc);
    printf("a=%s\n", a);
    printf("b=%s\n", b);
    printf("c=%s\n", c);
    printf("d=%s\n", d);
    printf("e=%s\n", e);
    printf("f=%s\n", f);
    printf("g=%s\n", g);

    FILE *fp = fopen("stata.lic", "r");
    if (!fp) {
        perror("fopen stata.lic");
        dlclose(handle);
        return 1;
    }

    char lic[4096];
    if (!fgets(lic, sizeof(lic), fp)) {
        fprintf(stderr, "failed to read stata.lic\n");
        fclose(fp);
        dlclose(handle);
        return 1;
    }
    fclose(fp);

    char *parts[8] = {0};
    int idx = 0;
    parts[idx++] = lic;
    for (char *p = lic; *p && idx < 8; ++p) {
        if (*p == '!') {
            *p = '\0';
            parts[idx++] = p + 1;
        }
    }

    if (!parts[1] || !parts[2]) {
        fprintf(stderr, "unexpected license layout\n");
        dlclose(handle);
        return 1;
    }

    char decoded[512];
    memset(decoded, 0, sizeof(decoded));
    int decode_rc = decode_fn(parts[1], parts[2], decoded);
    printf("decode_rc=%d\n", decode_rc);
    printf("decoded=%s\n", decoded);

    if (decode_rc == 0) {
        char sf5[128];
        char sf6[128];
        memset(sf5, 0, sizeof(sf5));
        memset(sf6, 0, sizeof(sf6));
        printf("field1=%d\n", int_field_fn(decoded, 1));
        printf("field2=%d\n", int_field_fn(decoded, 2));
        printf("field3=%d\n", int_field_fn(decoded, 3));
    printf("field4=%d\n", int_field_fn(decoded, 4));
        str_field_fn(sf5, decoded, 5, 0x24);
        str_field_fn(sf6, decoded, 6, 0x24);
        printf("field5=%s\n", sf5);
        printf("field6=%s\n", sf6);
    }

    char *base = (char *)info.dli_fbase;
    printf("g_serial=%s\n", base + 0x4fe5f60);
    printf("g_line1=%s\n", base + 0x4fe5f88);
    printf("g_line2=%s\n", base + 0x4fe6078);
    printf("g_f1=%d\n", *(int *)(base + 0x4fe5f80));
    printf("g_f2=%d\n", *(int *)(base + 0x4fe5f78));
    printf("g_f3=%d\n", *(int *)(base + 0x4fe5f7c));
    printf("g_f4=%d\n", *(int *)(base + 0x4fe5f84));
    printf("g_field5_char=%c\n", *(unsigned char *)(base + 0x4fe6168));
    printf("g_field5_group=%d\n", *(unsigned char *)(base + 0x4fe616b));
    printf("g_has_field6=%d\n", *(unsigned char *)(base + 0x4fe616c));
    printf("g_field5_gh=%d\n", *(unsigned char *)(base + 0x4fe616d));
    printf("g_mm=%d\n", *(int *)(base + 0x4fe6170));
    printf("g_dd=%d\n", *(int *)(base + 0x4fe6174));
    printf("g_yyyy=%d\n", *(int *)(base + 0x4fe6178));

    dlclose(handle);
    return 0;
}
