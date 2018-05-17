#!/usr/bin/env python3

from colorama import init, Fore
import os
import subprocess

def main(repo_url, site_path, domain):

    """Prepares the development environment with code repository cloning.
    """

    print('\nCloning AWS CodeCommit repo for static site...\n')
    subprocess.run(
        'git clone ' + repo_url + ' ' + site_path + '/src',
        shell=True
    )

    print('\nChecking local repo\'s remotes...\n')
    subprocess.run('git remote -v',shell=True)

    print('\nGenerating website index...')
    with open(site_path + '/src/index.html', "w") as config:
        txt_lines = [
        '<!DOCTYPE html>',
        '\n<html>',
        '\n  <head>',
        '\n    <meta charset="utf-8">',
        '\n    <title>' + domain + '</title>',
        '\n  </head>',
        '\n  <body>',
        '\n    <div style="text-align:center;">',
        '\n      <h1>' + domain + '</h1>',
        '\n    <div>',
        '\n  </body>',
        '\n</html>'
        ]
        config.writelines(txt_lines)

    print('\nStaging new file to local repo...')
    subprocess.run('git -C ' + site_path + '/src add -A', shell=True)

    print('\nCommitting staged file to local repo...\n')
    subprocess.run('git -C ' + site_path + '/src commit -m "test"', shell=True)

    print('\nPushing commit to remote AWS CodeCommit repo...\n')
    subprocess.run(
        'git -C ' + site_path + '/src push origin master',
        shell=True
    )

if __name__ == '__main__':
    main()
