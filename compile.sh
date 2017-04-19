#!/bin/sh
set -e -x

export name=atxmonc
export pkgrel=1

rm -rf build dist

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

python setup_win.py install --prefix=dist
# TODO: hack - include_msvcr seems to be broken in cx_freeze
cp -v c:/windows/system32/msvcp140.dll dist/

rm -rf pkg
mkdir pkg
mkdir -p pkg/$name
cp -av dist/* pkg/$name/

if [ -d pkg_data ]; then
  cp -rv pkg_data/* pkg/
fi

if [ -f atxpkg_backup ]; then
  cp -av atxpkg_backup pkg/.atxpkg_backup
fi

rm -rf build dist

if [ "$1" == "" ]; then
  export datetime=`gawk "BEGIN {print strftime(\"%Y%m%d%H%M%S\")}"`
  echo "devel version $datetime"
  export name=${name}.dev
  export version=$datetime
  export upload=atxpkg@atxpkg-dev.asterix.cz:atxpkg/
elif [ "$1" == "release" ]; then
  export version=`git describe --tags --abbrev=0`
  export version=${version:1}
  echo "release version $version"
  export upload=atxpkg@atxpkg.asterix.cz:atxpkg/
else
  echo "unknown parameter!"
  exit
fi

export pkg_fn=${name}-${version}-${pkgrel}.atxpkg.zip

rm -rf $pkg_fn

cd pkg
zip -r ../$pkg_fn .
cd ..

rm -rf pkg

rsync -avP $pkg_fn $upload
