mkdir rpmbuild
cd rpmbuild

planex-init
sed -i -e '/^DIST/ a MANIFEST=true' -e '/^DIST/ a RPM_EXTRA_DEFINES=--define "_sourcedir %_topdir/SOURCES/%name"' Makefile

ln -s /etc/mock mock

mkdir SPECS
ln -s ../../planex.spec SPECS

mkdir repos
ln -s ../.. repos/planex

mkdir PINS
cat > PINS/planex.pin <<EOF
{
  "URL": "ssh://git@github.com:xenserver/planex",
  "commitish": "master",
  "patchqueue": "master"
}
EOF