#!/bin/bash

GIT=$(which git)
DIR=`pwd`
REQ=$DIR/installation/requirements.txt
COMPONENTS=components
VE=`which virtualenv`
SETTINGS="components/settings.json"
PORT=5001
APPSECRET=$RANDOM$RANDOM$RANDOM$RANDOM
GITREPO=""

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
			cd $COMPONENTS
			$GIT init
			cd ..
			baseUrl="http://localhost:5001"
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
	if [ $GIT == "" ]; then
		echo "WARNING! Git not installed. Will copy default components without creating a git repository"
		defaultSettings
	else
		echo -n "Do you want to use an existing repository as a default component folder? Add URL if yes, empty otherwise: "
		read -u 1 GITREPO
		if [ "$GITREPO" != "" ]; then
			$GIT clone $GITREPO $COMPONENTS
                else
 			echo "Creating a brand new repository with default components"
			defaultSettings
		fi
	fi

fi



#Create new virtualenv

VE_DIR="flod_env_"$RANDOM

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

echo "Loading FLOD requirements"
$PIP -q install -r $REQ
#rdflib-jsonld is not installable via normal pip command
#$PIP install https://github.com/RDFLib/rdflib-jsonld/archive/master.zip

echo "Writing start.sh"
echo "#!/bin/bash" > start.sh
echo "source $VE_DIR/bin/activate" >> start.sh
echo "python flodserver.py" >> start.sh
echo "deactivate" >> start.sh

deactivate
chmod +x start.sh




echo
echo
echo "-----------------------------"
echo "To run FLOD, run:"
echo "# cd flod"
echo "# ./start.sh"
echo "-----------------------------"
