#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# region header
# Copyright Torben Sickert (info["~at~"]torben.website) 16.12.2012

# License
# -------

# This library written by Torben Sickert stand under a creative commons naming
# 3.0 unported license. see http://creativecommons.org/licenses/by/3.0/deed.de
# endregion
pkgname=webnode
pkgver=VERSION
pkgrel=3
pkgdesc='a high reliable python web library'
arch=('any')
url='http://torben.website/webNode'
license=('CC-BY-3.0')
depends=('python' 'python-sqlalchemy')
makedepends=('git' 'findutils')
optdepends=('sqlite: for sqlite database support'
            'nginx: for autoconfiguring them as proxy server')
source=('https://raw.githubusercontent.com/thaibault/webNode/master/webNode')
source=('git+https://github.com/thaibault/webNode')
md5sums=('SKIP')

pkgver() {
    cd webNode
    echo "1.0.r$(git rev-list --count HEAD)$(git rev-parse --short HEAD)"
}

package() {
    install --directory --mode 755 "${pkgdir}/usr/lib/python3.5"
    cp --recursive --force "${srcdir}/webNode" "${pkgdir}/usr/lib/python3.5"
    find "$pkgdir" -type f -not -name '*.py' -delete
    rm "${pkgdir}/.git" --recursive --force
    rm "${pkgdir}/documentation" --recursive --force
}
# region vim modline
# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:
# endregion
