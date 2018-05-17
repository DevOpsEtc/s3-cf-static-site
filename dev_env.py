#!/usr/bin/env python3

from colorama import init, Fore
import os
import subprocess
import sys

def main(home, repo_url, site_path, domain):

    """Prepares the development environment with code repository cloning.
    """

    logs = site_path + '/logs'  # raw log path
    report = '_report.html'     # log report name

    print('\nCloning AWS CodeCommit repo for static site...\n')
    subprocess.run(
        'git clone ' + repo_url + ' ' + site_path + '/src',
        shell=True
    )

    print('\nChecking local repo\'s remotes...\n')
    subprocess.run('git -C ' + site_path + '/src remote -v',shell=True)

    print('\nGenerating sample website index...')
    with open(site_path + '/deploy/build/index.html') as file:
        sub = (file.read().replace('$domain', domain))
    with open(site_path + '/src/index.html', "w") as file:
        file.write(sub)

    print('\nStaging new file to local repo...')
    subprocess.run('git -C ' + site_path + '/src add -A', shell=True)

    print('\nCommitting staged file to local repo...\n')
    subprocess.run('git -C ' + site_path + '/src commit -m "test"', shell=True)

    print('\nPushing commit to remote AWS CodeCommit repo...\n')
    subprocess.run(
        'git -C ' + site_path + '/src push origin master',
        shell=True
    )

    print('\nGenerating site log analyzer script...')
    with open(site_path + '/deploy/build/log_analyzer.sh') as file:
        sub = (file.read()
            .replace('$domain', domain)
            .replace('$site_path', site_path)
            .replace('$logs', logs)
            .replace('$report', report)
        )
    os.makedirs(site_path + '/bin', exist_ok=True)
    with open(site_path + '/bin/log_analyzer.sh', "w") as file:
        file.write(sub)

    print('\nSetting file mode on site log analyzer script to 755...')
    os.chmod(site_path + '/bin/log_analyzer.sh', 0o755)

    if sys.platform.startswith('darwin'):
        dotfile = home + '.bash_profile'
    elif sys.platform.startswith('linux'):
        dotfile = home + '.bashrc'

    if not 'alias slr' in open(dotfile).read():
        aliases = {
            'generate log analyzer locally: $ slr':
                'alias slr=\'' + site_path + '/bin/log_analyzer.sh\'\n',
            'delete log analyzer from S3 bucket: $ slrd':
                'alias slrd=\'aws s3 rm s3://' + domain + '/' + report + '\'\n'
        }

        for k, v in aliases.items():
            print('\nCreating bash alias to ' + k + '...')
            with open(dotfile, "a") as file:
                file.write(v)

        print('\nSource dotfile to pickup new aliases: $ source ' + dotfile)

if __name__ == '__main__':
    main()
