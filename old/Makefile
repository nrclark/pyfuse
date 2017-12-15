SRC := main.c
BIN := hellofs

MOUNT := yeek

$(BIN): $(SRC)
	gcc -D_FILE_OFFSET_BITS=64 $< -l fuse -o $@

mount: $(BIN)
	mkdir -p $(MOUNT)
	if mount | grep -q "on $(abspath $(MOUNT))"; then \
		fusermount -u $(MOUNT); \
	fi
	./$(BIN) $(MOUNT)

umount:
	if mount | grep -q "on $(abspath $(MOUNT))"; then \
		fusermount -u $(MOUNT); \
	fi

clean: umount
	rm -f $(BIN)
	rm -rf $(MOUNT)
