#!/usr/bin/env python3

from colorama import init, Fore
import os
import subprocess
import sys

def main(home, repo_ssh, site_path, domain):

    """Bootstraps a development environment with package installation, sample
    static website, repo cloning and ad-hoc management commands.
    """

    logs = site_path + '/logs'  # raw log path
    report = '_report.html'     # log report name
    hugo_theme = 'https://github.com/budparr/gohugo-theme-ananke.git'
    hugo_ver = subprocess.check_output(
        'curl --silent \
            "https://api.github.com/repos/gohugoio/hugo/releases/latest" | \
            grep "tag_name" | awk -Fv \'{gsub("\\"\,", ""); print $2}\'',
          shell=True,
          universal_newlines=True
    ).strip()
    cf_distro = subprocess.check_output(
        'aws cloudfront list-distributions --query "DistributionList.Items[? \
            contains(Aliases.Items, \'' + domain + '\')].Id" --output text',
          shell=True,
          universal_newlines=True
    ).strip()

    print('\nInitializing new git repo...\n')
    os.makedirs(site_path + '/src', exist_ok=True)
    subprocess.run('git -C ' + site_path + '/src init', shell=True)

    print('\nAdding remote repo to new local repo...')
    subprocess.run('git -C ' + site_path + '/src remote add origin '
        + repo_ssh,
        shell=True
    )

    print('\nVerifying local repo\'s new remote...\n')
    subprocess.run('git -C ' + site_path + '/src remote -v', shell=True)

    print('\nGenerating AWS CodeBuild buildspec for production...')
    with open(site_path + '/deploy/build/buildspec_prod.yaml') as file:
        sub = (file.read()
            .replace('$hugo_ver', hugo_ver)
            .replace('$s3_bucket', domain)
            .replace('$cf_distro', cf_distro)
        )
    os.makedirs(site_path + '/src/config', exist_ok=True)
    with open(site_path + '/src/config/buildspec_prod.yaml', "w") as file:
        file.write(sub)

    try:
        subprocess.check_output(['type', '-p', 'hugo'])
    except subprocess.CalledProcessError:
        print(Fore.YELLOW + '\nHugo not found, please install and rerun')
        print('\nhttps://gohugo.io/getting-started/installing/' + Fore.RESET)
        exit()

    print('\nGenerating new Hugo static site...')
    # force lets us install in non-empty directory, e.g. .git
    subprocess.run('hugo new site ' + site_path + '/src --force > /dev/null',
        shell=True
    )

    print('\nCloning a sample Hugo theme...\n')
    subprocess.run(
        'git -C ' + site_path + '/src clone ' + hugo_theme + ' themes/ananke \
        && rm -rf ' + site_path + '/src/themes/ananke/.git',
        shell=True
    )

    print("\nAdding the sample Hugo theme to your new Hugo site's config...")
    subprocess.run(
        'echo \'theme = "ananke"\' >> ' + site_path + '/src/config.toml',
        shell=True
    )

    print("\nAdding your domain to your new Hugo site...")
    subprocess.run(
        'sed -i \'\' "/baseURL/d" ' + site_path + '/src/config.toml && \
        echo \'baseURL = "https://devopsetc.com/"\' >> ' + site_path +
        '/src/config.toml',
        shell=True
    )

    print('\nAdding a sample post to your new Hugo site...\n')
    subprocess.run('hugo -s ' + site_path + '/src new post/test.md && \
        sed -i \'\' "s/true/false/" ' + site_path + '/src/content/post/test.md',
        shell=True
    )

    print(Fore.YELLOW +
        '\nRun Hugo server with drafts enabled:'
        '\n$ hugo server -D  # Press Ctrl+C to stop'
        '\nView new website at http://localhost:1313/'
        + Fore.RESET
    )

    print('\nStaging new files to local repo...')
    subprocess.run('git -C ' + site_path + '/src add -A', shell=True)

    print('\nCommitting staged files to local repo...\n')
    subprocess.run('git -C ' + site_path + '/src commit -m "test"', shell=True)

    print('\nPushing commit to remote AWS CodeCommit repo...\n')
    subprocess.run(
        'git -C ' + site_path + '/src push -f -u origin master',
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
