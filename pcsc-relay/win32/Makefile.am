EXTRA_DIST = libnfc_mingw.patch


all-local:
	echo "Use \`make win\` to cross compile for Windows"


IMAGE=$(abs_builddir)/image


LIBNFC_DIR=$(abs_builddir)/libnfc
LIBNFC_DLL=$(IMAGE)/bin/libnfc-3.dll
$(LIBNFC_DIR)/configure.ac:
	svn co -r1327 http://libnfc.googlecode.com/svn/trunk $(LIBNFC_DIR)
$(LIBNFC_DLL): $(LIBNFC_DIR)/configure.ac
	grep i686-w64-mingw32 $(LIBNFC_DIR)/mingw-cross-configure.sh > /dev/null || \
		patch -p0 -d $(LIBNFC_DIR) < libnfc_mingw.patch
	cd $(LIBNFC_DIR) && sh mingw-cross-configure.sh --prefix=$(IMAGE)
	make -C $(LIBNFC_DIR) install


MINGW ?= i686-w64-mingw32
MINGW_DIR=/usr/$(MINGW)
PCSC_RELAY_EXE=$(IMAGE)/bin/pcsc-relay.exe
$(PCSC_RELAY_EXE): $(LIBNFC_DLL)
	cd $(abs_top_builddir) && ./configure \
		--prefix=$(IMAGE) \
		--host=$(MINGW) --target=$(MINGW) \
		PKG_CONFIG_LIBDIR=$(IMAGE)/lib/pkgconfig \
		CFLAGS=-I$(MINGW_DIR)/include \
		LDFLAGS=-L$(MINGW_DIR)/lib \
		PCSC_LIBS="-lwinscard"
	make -C $(abs_top_builddir) install


LIBUSB_DLL=$(LIBNFC_DIR)/libusb-win32-bin-*/bin/x86/libusb0_x86.dll
WIN32_DIR=$(abs_top_builddir)/$(PACKAGE_TARNAME)-$(PACKAGE_VERSION)_win32
win: $(PCSC_RELAY_EXE)
	$(INSTALL) -d $(WIN32_DIR)
	$(INSTALL_PROGRAM) -t $(WIN32_DIR) \
		$(LIBNFC_DLL) $(PCSC_RELAY_EXE)
	$(INSTALL_PROGRAM) $(LIBUSB_DLL) $(WIN32_DIR)/libusb0.dll

clean-local:
	rm -rf $(IMAGE) $(WIN32_DIR)
	test ! -d $(LIBNFC_DIR) || \
		make -C $(LIBNFC_DIR) clean

distclean-local:
	rm -rf $(LIBNFC_DIR)
