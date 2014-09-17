[actor] @dbtype:mem,fs
    """
    Operator actions to perform interventions on cloudspaces
    """
    method:destroy
        """
        destroy a cloudspace
        """
        var:accountname str,,name of account
        var:cloudspaceName str,,name of cloudspace
        var:cloudspaceId str,,ID of cloudspace
        var:reason str,, reason for destroying the cloudspace

    method:moveVirtualFirewallToFirewallNode
        """
        move the virtual firewall of a cloudspace to a different firewall node
        """
        var:cloudspaceId int,, id of the cloudspace
        var:targetNode str,, name of the firewallnode the virtual firewall has to be moved to

    method:restoreVirtualFirewall
        """
        Restore the virtual firewall of a cloudspace on an available firewall node
        """
        var:cloudspaceId int,, id of the cloudspace

    method:addExtraIP
        """
        Adds an available public IP address
        """
        var:cloudspaceId int,, id of the cloudspace
        var:ipaddress str,, only needed if a specific IP address needs to be assigned to this space @optional

    method:removeIP
        """
        Removed a public IP address from the cloudspace
        """
        var:cloudspaceId int,, id of the cloudspace
        var:ipaddress str,, public IP address to remove from this cloudspace