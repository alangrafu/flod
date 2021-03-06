#!/bin/bash

options=$@
index=0
arguments=($options)

GIT=$(which git)
DIR=`pwd`
REQ=$DIR/installation/requirements.txt
COMPONENTS=components
ADDREQ=$COMPONENTS/requirements.txt
TEMPLATES=templates
VE=`which virtualenv`
SETTINGS="components/settings.json"
PORT=54321
APPSECRET=$RANDOM$RANDOM$RANDOM$RANDOM
GITREPO=""


for argument in $options
  do
    # Incrementing index
    index=`expr $index + 1`

    # The conditions
    case $argument in
      repo-url=*) val=${argument#*=};
                  opt=${argument%=$val};
                  GITREPO="${val}" ;;
    esac
done
#Create new virtualenv

VE_DIR="_flod_env_"$RANDOM

echo "Creating virtualenv $VE_DIR..."
$VE -q $VE_DIR
source $VE_DIR/bin/activate


PIP=`which pip`
if [ -z "$PIP" ]; then
	echo "You need pip installed. Run"
	echo "  sudo easy_install -U pip"
	echo "and then execute installation/install.sh again"
	deactivate
	exit 1
fi




#Detecting neede tools

if [ -z "$VE" ]; then
	echo "You need virtualenv installed. Run"
	echo "  sudo easy_install -U virtualenv"
	echo "and then execute installation/install.sh again"
	exit 1
fi

function defaultSettings {
	#Ask questions:
			cp -r installation/defaultComponents $COMPONENTS
			cp -r installation/defaultTemplates $TEMPLATES
			cd $COMPONENTS
			$GIT init
			cd ..
			baseUrl="http://localhost:54321"
			echo -n "(1/3) Whats your domain name? (default '$baseUrl'): "
			read -u 1 aux_baseUrl
			echo
			if [ "$aux_baseUrl" != "" ]; then
			  baseUrl=$aux_baseUrl
			fi
			aux_port=$(echo $baseUrl |awk -F":" '{print $3}')
			if [ "$aux_port" != "" ]; then
			  PORT=$aux_port
			fi

			baseUrl="`echo $baseUrl | sed 's/\/$//'`" # remove any ending slash
			ns=$baseUrl/
			echo    "(2/3) What local namespace of your data?"
			echo -n "(default '$ns'): "
			read -u 1 aux_ns
			echo ""
			if [ "$aux_ns" != "" ]; then
			  aux_ns="`echo $aux_ns | sed 's/\/$//'`" # remove any ending slash and append one.
			  ns=$aux_ns
			fi

			endpoint=$baseUrl/sparql
			echo    "(3/3) What is the URL of your SPARQL endpoint?"
			echo -n "(default $endpoint): "
			read -u 1 aux_endpoint
			echo ""
			if [ "$aux_endpoint" != "" ]; then
			  endpoint=$aux_endpoint
			fi


			if [ -e $SETTINGS ]; then
				NOW=$(date +"%s")
				echo "WARNING: Moving existing $SETTINGS to $SETTINGS.$NOW"
				mv "$SETTINGS"  "$SETTINGS.$NOW"
			fi

			echo "{" >> $SETTINGS
			echo " 	\"modules\": [ \"Static\", \"Users\", \"Services\", \"Types\"]," >> $SETTINGS
			echo " 	\"ns\": {" >> $SETTINGS
			echo " 		\"local\": \"$baseUrl/\"," >> $SETTINGS
			echo " 		\"origin\": \"$ns/\"" >> $SETTINGS
			echo " 	}," >> $SETTINGS
			echo " 	\"mirrored\": true," >> $SETTINGS
			echo " 	\"endpoints\": {" >> $SETTINGS
			echo " 		\"local\": \"$endpoint\"," >> $SETTINGS
			echo " 		\"dbpedia\": \"http://dbpedia.org/sparql\"" >> $SETTINGS
			echo " 	}," >> $SETTINGS
			echo " 	\"host\": \"0.0.0.0\"," >> $SETTINGS
			echo " 	\"port\": $PORT", >> $SETTINGS
			echo " 	\"flod\": { ">> $SETTINGS
			echo " 	  \"title\": \"FLOD\"" >> $SETTINGS
			echo " 	}," >> $SETTINGS
			echo " 	\"secret\": \"$APPSECRET\"", >> $SETTINGS
			echo " 	\"root\": \"home\"" >> $SETTINGS
			echo "}" >> $SETTINGS
			cd $COMPONENTS
			$GIT add .
			$GIT commit -a -m "first import of flod components"
			cd ..		
}


#Copying components
if [ -e "$COMPONENTS" ]; then
	echo "WARNING! Components folder already exist. Installation WILL NOT OVERRIDE IT"
else
	echo "Copying default components"
	if [ "$GIT" == "" ]; then
		echo "WARNING! Git not installed. Will copy default components without creating a git repository"
		defaultSettings
	else
		if [ "$GITREPO" == "" ]; then
	                echo "--------------------------------"
        	        echo "For a tutorial application, use this URL"
                	echo ""
 	                echo https://github.com/alangrafu/flod-tutorial-app
        	        echo ""
                	echo "--------------------------------"
			echo -n "Do you want to use an existing repository as a default component folder? Add URL if yes, empty otherwise: "
			read -u 1 GITREPO
		fi
		if [ "$GITREPO" != "" ]; then
			$GIT clone $GITREPO $COMPONENTS
			if [ -e "$ADDREQ" ]; then
				echo "Installing custom requirements"
				$PIP -q install -r $ADDREQ
			fi
                else
 			echo "Creating a brand new repository with default components"
			defaultSettings
		fi
	fi

fi



echo "Loading FLOD requirements"
$PIP -q install -r $REQ
#rdflib-jsonld is not installable via normal pip command
#$PIP install https://github.com/RDFLib/rdflib-jsonld/archive/master.zip
echo "Copying users.ttl"
cp installation/users.ttl .

echo "Writing start.sh"
echo "#!/bin/bash" > start.sh
echo "source $VE_DIR/bin/activate" >> start.sh
echo "SETTINGS=\"components/settings.json\"" >> start.sh
echo "if [ \$# -gt 0 ]; then" >> start.sh
echo "  SETTINGS=\$1" >> start.sh
echo "fi" >> start.sh
echo "" >> start.sh
echo "HOST=\$(cat \$SETTINGS |python -c 'import json,sys;obj=json.load(sys.stdin);print obj[\"host\"]')" >> start.sh
echo "PORT=\$(cat \$SETTINGS |python -c 'import json,sys;obj=json.load(sys.stdin);print obj[\"port\"]')" >> start.sh
echo "echo Launching FLOD on \$HOST:\$PORT >&2" >> start.sh
echo "uwsgi --http \$HOST:\$PORT -wflodserver:app --master --workers=2 --threads=10 --pidfile .pid --pyargv \$SETTINGS" >> start.sh
echo "deactivate" >> start.sh
TMP=settings_$RANDOM
cat components/settings.json |python -c 'import json,sys,uuid;obj=json.load(sys.stdin);obj["secret"]=str(uuid.uuid4());print json.dumps(obj, indent=4)' > $TMP
mv $TMP components/settings.json
deactivate
chmod +x start.sh




echo
echo
echo "-----------------------------"
echo "To run FLOD, run:"
echo "# cd flod"
echo "# ./start.sh"
echo "-----------------------------"
