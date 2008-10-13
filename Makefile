include ../Makefile.common

all:

install: all
	$(INSTALL) -d -m 755 '$(DESTDIR)$(bindir)'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka/dialogs'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka/glade'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka/graphics'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka/helper'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/sushi/tekka/plugins'
	$(INSTALL) -d -m 755 '$(DESTDIR)$(sharedir)/applications'
	$(INSTALL) -m 644 *.py '$(DESTDIR)$(sharedir)/sushi/tekka'
	$(INSTALL) -m 644 dialogs/*.py '$(DESTDIR)$(sharedir)/sushi/tekka/dialogs'
	$(INSTALL) -m 644 glade/*.glade '$(DESTDIR)$(sharedir)/sushi/tekka/glade'
	# FIXME
	$(SED) 's#@SUSHI_VERSION@#$(SUSHI_VERSION)#' 'glade/dialogs.glade' > '$(DESTDIR)$(sharedir)/sushi/tekka/glade/dialogs.glade'
	$(INSTALL) -m 644 graphics/*.svg '$(DESTDIR)$(sharedir)/sushi/tekka/graphics'
	$(INSTALL) -m 644 helper/*.py '$(DESTDIR)$(sharedir)/sushi/tekka/helper'
	$(INSTALL) -m 644 plugins/*.py '$(DESTDIR)$(sharedir)/sushi/tekka/plugins'
	$(SED) 's#@bindir@#$(bindir)#' 'tekka.desktop' > '$(DESTDIR)$(sharedir)/applications/tekka.desktop'
	$(CHMOD) +x '$(DESTDIR)$(sharedir)/sushi/tekka/main.py'
	$(LN) '$(sharedir)/sushi/tekka/main.py' '$(DESTDIR)$(bindir)/tekka'

	$(MAKE) -C po $@

clean:
	$(RM) *.pyc

	$(MAKE) -C po $@
