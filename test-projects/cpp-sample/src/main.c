/*
 * Sample C Application
 * Copyright (c) 2024 Example Corporation
 * Licensed under MIT License
 */

#include <stdio.h>
#include <stdlib.h>
#include "cJSON.h"

int main(int argc, char *argv[]) {
    printf("Sample C Application with OSS libraries\n");

    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "message", "Hello from cJSON");
    cJSON_AddNumberToObject(root, "version", 1);

    char *json_string = cJSON_Print(root);
    printf("JSON: %s\n", json_string);

    free(json_string);
    cJSON_Delete(root);

    return 0;
}
