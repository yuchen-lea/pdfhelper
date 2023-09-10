.PHONY: install uninstall

DESTDIR=
PREFIX=/usr/local

CP=cp
INSTALL=install
LN=ln
MKDIR=mkdir -p
RM=rm -f -v

install:
	$(MKDIR) "$(DESTDIR)$(PREFIX)/share/pdfhelper"
	$(INSTALL) -m0755 *.py "$(DESTDIR)$(PREFIX)/share/pdfhelper/"
	$(CP) *.ini "$(DESTDIR)$(PREFIX)/share/pdfhelper/"
	$(MKDIR) "$(DESTDIR)$(PREFIX)/bin"
	$(LN) -sf "$(PREFIX)/share/pdfhelper/pdfhelper.py" "$(DESTDIR)$(PREFIX)/bin/pdfhelper"

uninstall:
	$(RM) -R "$(DESTDIR)$(PREFIX)/bin/pdfhelper" "$(DESTDIR)$(PREFIX)/share/pdfhelper"
