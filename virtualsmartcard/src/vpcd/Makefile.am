VPCD_LIB = $(LIB_PREFIX)vpcd.$(DYN_LIB_EXT)

lib_LTLIBRARIES = libvpcd.la
libvpcd_la_SOURCES = ifd-vpcd.c vpcd.c
libvpcd_la_LIBADD = $(PCSC_LIBS)
libvpcd_la_LDFLAGS = -no-undefined
libvpcd_la_CFLAGS = $(PCSC_CFLAGS)

noinst_HEADERS = vpcd.h

EXTRA_DIST = reader.conf.in


do_subst = $(SED) -e 's,[@]TARGET[@],$(serialdropdir)/$(VPCD_LIB),g'


install: install_libvpcd

install_libvpcd: libvpcd.la reader.conf.in
	$(mkinstalldirs) $(DESTDIR)$(serialdropdir)
	$(LIBTOOL) --mode=install cp .libs/$(VPCD_LIB) $(DESTDIR)$(serialdropdir)/$(VPCD_LIB).$(VERSION)
	(cd $(DESTDIR)$(serialdropdir) && \
		$(LN_S) -f $(VPCD_LIB).$(VERSION) $(VPCD_LIB))
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)/reader.conf.d
	$(do_subst) < $(srcdir)/reader.conf.in > $(DESTDIR)$(sysconfdir)/reader.conf.d/vpcd


uninstall: uninstall_libvpcd

uninstall_libvpcd:
	rm -f $(DESTDIR)$(serialdropdir)/$(VPCD_LIB).$(VERSION) \
	    $(DESTDIR)$(serialdropdir)/$(VPCD_LIB) \
	    $(DESTDIR)$(sysconfdir)/reader.conf.d/vpcd
