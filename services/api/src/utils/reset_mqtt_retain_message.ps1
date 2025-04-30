    # Replace placeholders with your actual EMQX details
    $emqxHost = "z8002768.ala.us-east-1.emqxsl.com"
    $emqxPort = 8883
    $emqxTopic = "campus/security/emergency"
    $caCertPath = "..\certs\emqxsl-ca.crt" # Use the correct path to your CA cert
    $emqxUser = "kalebcole" # Omit -u and -P if no auth
    $emqxPass = "cses" # Omit -u and -P if no auth

    # Command to publish an empty retained message
    mosquitto_pub -h $emqxHost -p $emqxPort -t $emqxTopic -m "" -r -q 1 --cafile $caCertPath -u $emqxUser -P $emqxPass