PREFIX ?= /usr/local

all: dell-ir-grab

dell-ir-grab: ir-grab.cpp
	$(CXX) -std=c++17 -O2 $< -o $@ $$(pkg-config --cflags --libs libcamera) -pthread

install: dell-ir-grab
	install -Dm755 dell-ir-grab $(DESTDIR)$(PREFIX)/libexec/dell-ir-grab

clean:
	$(RM) dell-ir-grab
