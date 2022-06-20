function A = GrowRandomGraph(A,degree,corrupt,sybil)
%GROWRANDOMGRAPH Simmulates a trust graph of sybil, corrupt and honest identities
%   A - adjacency matrix of an HCS graph
%   degree - maximum degree of the graph
%   corrupt - number of corrupt identities
%   sybil - number of sybil identities

    % initialize an adjacency matrix of 'nodes' nodes
    nodes = size(A,1);
    failedAttempts=0;
    lastHonest=nodes-sybil-corrupt;
    lastCorrupt=nodes-sybil;

    % loop while minimal degree < 'degree'-1
    while min(sum(A)) < degree-1
        % pick a random node with not enough edges
        desolatedNodes = find(sum(A)<degree-1);
        v = desolatedNodes(randi(length(desolatedNodes)));
        
        % pick nodes with room for another edge
        applicableNodes = (sum(A)<degree);
        % that are not connected to v
        applicableNodes(v)=0;
        applicableNodes(logical(A(v,:)))=0;
        % if v is sybil, don't connect to honest
        if v > lastCorrupt
            applicableNodes(1:lastHonest)=0;
        end
        % if v is honest, don't connect to sybil
        if v <= lastHonest
            applicableNodes((lastCorrupt+1):end)=0;
        end
        applicableNodes = find(applicableNodes);
        
        % if no applicable node, report an error
        if(isempty(applicableNodes))
            disp('Failed to find a partner');
            failedAttempts = failedAttempts+1;
            if(failedAttempts>1000)
                break;
            end
            continue;
        end
        
        % pick one at random and connect
        u = applicableNodes(randi(length(applicableNodes)));
        A(u,v)=1;
        A(v,u)=1;
        B = repmat(sum(A),nodes,1)+repmat(sum(A,2),1,nodes);
        A(B==degree*2) = 0;
    end
end

