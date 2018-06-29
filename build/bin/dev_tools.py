#!/usr/bin/env python3

# include standard modules
import getopt
import os
import signal
import subprocess
import sys

# include 3rd party modules
from colorama import init, Fore

# include custom modules
sys.path.append('$site_deploy')
import deploy
import key_gen

def main():

    """Bootstraps a development environment with ad-hoc management commands
    that can install, uninstall, rotate key pair, generate a site log report
    and start/stop a watched development session.
    """
    home = os.path.expanduser('~/')     # expand home directory
    site_root = home + '$domain'        # path to site root
    site_dpl = site_root + '/deploy'    # path to site deploy
    site_src = site_root + '/src'       # path to site source
    site_bld = site_src + '/build'      # path to site build
    site_log = site_root + '/logs'      # path to site logs
    report = '_report.html'             # name of log report

    fullCmdArgs = sys.argv              # read commandline arguments (first)
    argList = fullCmdArgs[1:]           # further arguments

    # valid parameters
    shortOps = 'cdhikloprsux'
    longOps = [
        'dev',
        'dev-clean',
        'dev-stop',
        'dev-style',
        'help',
        'install',
        'keypair',
        'log',
        'new-post',
        'open',
        'uninstall'
    ]

    if len(sys.argv) == 1:
        opt_error()
        sys.exit(1)

    try:
        arguments, values = getopt.getopt(argList, shortOps, longOps)
    except getopt.error as err:
        opt_error(err)

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-i", "--install"):
            deploy.main()
        elif currentArgument in ("-k", "--keypair"):
            key_gen.main()
        elif currentArgument in ("-u", "--uninstall"):
            print ("Static-Site Uninstall Coming Soon")
        elif currentArgument in ("-d", "--dev"):
            dev_stop()
            dev(site_src, site_bld)
            site_open()
        elif currentArgument in ("-s", "--dev-style"):
            dev_stop()
            dev(site_src, site_bld)
            dev_style(site_bld)
            site_open()
        elif currentArgument in ("-c", "--dev-clean"):
            dev_clean(site_bld)
        elif currentArgument in ("-x", "--dev-stop"):
            dev_stop()
        elif currentArgument in ("-o", "--open"):
            site_open()
        elif currentArgument in ("-p", "--new-post"):
            site_post(site_src)
        elif currentArgument in ("-r", "--report"):
            site_report(site_root, site_log, report)
        elif currentArgument in ("-h", "--help"):
            help()
        else:
            opt_error()

def opt_error(err = 'No valid option entered!'):
    print('\n' + Fore.YELLOW + str(err) + Fore.RESET)
    help()
    if len(sys.argv) > 1:
        sys.exit(1)

def help():
    print (Fore.GREEN +
        '\n$ site -i or $ site --install    # Deploy static site to AWS '
            'cloud and local'
        '\n$ site -d or $ site --dev        # Run webpack build and enable '
            'file watch mode'
        '\n$ site -s or $ site --dev-style  # Run Webpack build and enable '
            'file watch mode +CSS'
        '\n$ site -c or $ site --dev-clean  # Remove webpack generated static '
            'files'
        '\n$ site -x or $ site --dev-stop   # Disable Hugo and Webpack file '
            'watch mode'
        '\n$ site -k or $ site --keypair    # Rotate SSH key pair'
        '\n$ site -o or $ site --open       # Open localhost site in browser'
        '\n$ site -p or $ site --new-post   # Create new Hugo post'
        '\n$ site -r or $ site --report     # Download site access logs and '
            'generate analysis report'
        '\n$ site -u or $ site --uninstall  # Uninstall static site from AWS'
            'cloud and local'
        + Fore.RESET)

def dev(site_src, site_bld):
    os.chdir(site_bld)  # change cwd to site build
    subprocess.run('yarn start', shell=True)  # yarn clean & yarn build source
    os.chdir(site_src)  # change cwd to site source
    subprocess.run('hugo server -D &', shell=True)  # build and serve dev site
    print(Fore.YELLOW + '\nPress enter to get prompt back!\n' + Fore.RESET)

def dev_style(site_bld):
    os.chdir(site_bld)
    subprocess.run('yarn dev &', shell=True)  # yarn clean & yarn build source

def dev_clean(site_bld):
    os.chdir(site_bld)
    subprocess.run('yarn clean', shell=True)

def site_open():
    if sys.platform.startswith('darwin'):
        subprocess.run('open http://localhost:1313', shell=True)

def dev_stop():
    processes = ['hugo', 'webpack']
    for process in processes:
        try:
            # throw into list for cases when pattern match yields multiple pids
            pids = subprocess.check_output(['pgrep', '-f', process],
                universal_newlines=True).split('\n')

            # strip empty elements and convert back to list
            pids = list(filter(None, pids))

            # map list from strings to integers
            pids = list(map(int, pids))

            for pid in pids:
                os.kill(pid, signal.SIGTERM)

            print(Fore.YELLOW + '- Process terminated: ' + process +
                Fore.RESET)
        except:
            pass

def site_post(site_src):
    os.chdir(site_src)  # change cwd to site source
    post_title = input(Fore.GREEN + '\nEnter a title for your new post '
    '(no spaces): ' + Fore.RESET)
    subprocess.run('hugo new post/' + post_title + '.md', shell=True)

def site_report(site_root, site_log, report):
    if os.path.isfile(site_log + '/' + report):
        os.remove(site_log + '/' + report)

    subprocess.run('aws s3 sync --exclude "Static-Site-CICD-Sit/*" '
        's3://log.$domain ' + site_root, shell=True
    )

    if sys.platform.startswith('darwin'):
        log_proc = 'gunzip -c ' + site_log + '/*.gz | goaccess -a -o'

    elif sys.platform.startswith('linux'):
        log_proc = 'zcat ' + site_log + '/*.gz | goaccess -a -o'

    else:
        print(Fore.YELLOW + 'Script not supported on this OS' + Fore.RESET)
        sys.exit(1)

    subprocess.run(log_proc + ' ' + site_log + '/' + report, shell=True)

    print('\nSite log report generated: ' + site_log + '/' + report)

    if sys.platform.startswith('darwin'):
        subprocess.run('open ' + site_log + '/' + report, shell=True)

if __name__ == '__main__':
    main()
