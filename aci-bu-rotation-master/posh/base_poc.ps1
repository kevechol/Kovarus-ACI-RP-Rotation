$user = "svc.network"
$password = ConvertTo-SecureString -String "!Passw0rd" -AsPlainText -Force
$creds = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $user, $password

$payload = "{
  ""ins_api"": {
            ""version"": ""1.2"",
            ""type"": ""cli_show"",
            ""chunk"": ""0"",
            ""sid"": ""1"",
            ""input"": ""show interface eth1/1"",
            ""output_format"": ""json""
            }
}"

$result = Invoke-RestMethod -Uri http://10.1.0.2/ins -Method post -Credential $creds -ContentType "application/json" -Body $payload

$result.ins_api.outputs.output.body.TABLE_interface.ROW_interface