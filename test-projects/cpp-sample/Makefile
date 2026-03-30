CC = gcc
CFLAGS = -I./third-party/cjson -I./third-party/zlib -I./third-party/mbedtls
LDFLAGS = -lz -lssl -lcrypto

all: app

app: src/main.c third-party/cjson/cJSON.c
	$(CC) $(CFLAGS) -o app src/main.c third-party/cjson/cJSON.c $(LDFLAGS)

clean:
	rm -f app compile_commands.json
