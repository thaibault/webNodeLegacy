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
pkgver=1.0.2
pkgrel=5
pkgdesc='a high reliable python web library'
arch=('any')
url='http://torben.website/webNode'
license=('CC-BY-3.0')
depends=('python' 'python-sqlalchemy' 'boostnode')
makedepends=('git' 'findutils')
optdepends=('sqlite: for sqlite database support'
            'nginx: for autoconfiguring them as proxy server')
source=('.')
md5sums=('SKIP')

package() {
    install --directory --mode 755 "${pkgdir}/usr/lib/python3.5"
    find "$scrdir" -type f -not -name '*.py' -delete
    rm "${scrdir}/.git" --recursive --force
    rm "${scrdir}/documentation" --recursive --force
    cp --recursive --force "${srcdir}" "${pkgdir}/usr/lib/python3.5"
}
# region vim modline
# vim: set tabstop=4 shiftwidth=4 expandtab:
# vim: foldmethod=marker foldmarker=region,endregion:
# endregion
