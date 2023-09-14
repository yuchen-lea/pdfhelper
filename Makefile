.PHONY: install update uninstall

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
	$(CP) *.example "$(DESTDIR)$(PREFIX)/share/pdfhelper/"
	for file in *.example; do \
		$(CP) -f "$$file" "$(DESTDIR)$(PREFIX)/share/pdfhelper/`basename $$file .example`"; \
	done
	$(MKDIR) "$(DESTDIR)$(PREFIX)/bin"
	$(LN) -sf "$(PREFIX)/share/pdfhelper/pdfhelper.py" "$(DESTDIR)$(PREFIX)/bin/pdfhelper"

update:
	$(INSTALL) -m0755 *.py "$(DESTDIR)$(PREFIX)/share/pdfhelper/"
	$(CP) -f *.example "$(DESTDIR)$(PREFIX)/share/pdfhelper/"

uninstall:
	$(RM) -R "$(DESTDIR)$(PREFIX)/bin/pdfhelper" "$(DESTDIR)$(PREFIX)/share/pdfhelper"
