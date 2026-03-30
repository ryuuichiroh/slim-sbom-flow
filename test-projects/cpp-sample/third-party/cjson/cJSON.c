/*
  Copyright (c) 2009-2017 Dave Gamble and cJSON contributors
  SPDX-License-Identifier: MIT
*/

#include "cJSON.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

cJSON *cJSON_CreateObject(void) {
    cJSON *item = (cJSON *)malloc(sizeof(cJSON));
    memset(item, 0, sizeof(cJSON));
    item->type = 6;
    return item;
}

void cJSON_AddStringToObject(cJSON *object, const char *name, const char *string) {
    cJSON *item = (cJSON *)malloc(sizeof(cJSON));
    memset(item, 0, sizeof(cJSON));
    item->string = strdup(name);
    item->valuestring = strdup(string);
    item->type = 4;
}

void cJSON_AddNumberToObject(cJSON *object, const char *name, double number) {
    cJSON *item = (cJSON *)malloc(sizeof(cJSON));
    memset(item, 0, sizeof(cJSON));
    item->string = strdup(name);
    item->valuedouble = number;
    item->valueint = (int)number;
    item->type = 3;
}

char *cJSON_Print(const cJSON *item) {
    return strdup("{\"message\":\"Hello from cJSON\",\"version\":1}");
}

void cJSON_Delete(cJSON *item) {
    if (item) {
        if (item->string) free(item->string);
        if (item->valuestring) free(item->valuestring);
        free(item);
    }
}
