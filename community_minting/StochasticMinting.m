function [mintHistory,treasury,dead, inDebt] = StochasticMinting(honest,corrupt,sybil,degree,rounds,expProb,deathProb)
%STOCHASTICMINTING Simmulates minting money in an HCS graph
%   A - adjacency matrix of an HCS graph
%   degree - maximum degree of the graph
%   corrupt - number of corrupt identities
%   sybil - number of sybil identities
%   rounds - number of rounds to run the simmulation

  % initialize the history matrix
  nodes = honest+corrupt+sybil;
  A=zeros(nodes,nodes,rounds);
  A(:,:,1)=GrowRandomGraph(A(:,:,1),degree,corrupt,sybil);
  mintHistory = zeros(rounds,nodes);
  accountedHistory = zeros(rounds,nodes);
  inDebt = zeros(rounds,nodes);
  dead = zeros(rounds,nodes);
  treasury = 0;
  lastCorrupt=nodes-sybil;
  sybilVec = [zeros(1,honest+corrupt),ones(1,sybil)];
  shifter = repmat(1:nodes,rounds,1);

  f4=figure('name','inDebt');
    
  for round=1:rounds
    % tag debts
    inDebtMint = double(any(inDebt.*(~dead)));
    % mint money
    mintHistory(round,inDebtMint==0) = 1;
    accountedHistory(round,:) = 1;
    % half the debt acts as punishment and half annulates excessive money
    for secRound = 1:round
      if ~any(inDebtMint)
        break;
      end
      payments = min([inDebt(secRound,:);inDebtMint;~dead(secRound,:)]);
      inDebt(secRound,:) = inDebt(secRound,:)-payments;
      treasury = treasury + sum(payments)/2;
      inDebtMint = inDebtMint-payments;
    end
    mintHistory(round,:) = mintHistory(round,:)+inDebtMint;
        
    % fish a sybil
    probs=rand(1,nodes);
    probs(1:lastCorrupt)=(probs(1:lastCorrupt)<deathProb);
    probs(lastCorrupt+1:end)=(probs(lastCorrupt+1:end)<expProb);

    for v = find(probs)
      if(v>lastCorrupt)
        debt = accountedHistory(:,v)*2 + inDebt(:,v);
        accountedHistory(1:round,v) = 0;
        inDebt(1:round,v) = 0;
        dead(1:round,v)=1;
                
        indexes = find(debt);
        for index=1:length(indexes)
          secRound=indexes(index);
          % find active neighbours
          neighbours = (A(v,:,secRound)==1);
          visited=neighbours;
          visited(v)=1;
          while ~isempty(find(neighbours & dead(secRound,:) & sybilVec, 1))
            secondNeighbours = any([A(neighbours & dead(secRound,:) & sybilVec,:,secRound);zeros(1,nodes)]);
            secondNeighbours = secondNeighbours & ~visited;
            neighbours = (neighbours & (~dead(secRound,:) | ~sybilVec)) | secondNeighbours;
            visited = visited | neighbours;
          end
          % fix their debt to cover for the sybil
          if(sum(neighbours & ~dead(secRound,:))>0)
            neighbours = (neighbours & ~dead(secRound,:));
          end
          inDebt(secRound,neighbours) = inDebt(secRound,neighbours)+debt(secRound)/sum(neighbours);
        end
      else
        dead(1:round,v)=1;
      end

      % prepare next round
      if round<rounds
        A(:,:,round+1)=A(:,:,round);
        A(v,:,round+1) = 0;
        A(:,v,round+1) = 0;
      end
    end

    % reconnect the graph with a new sybil
    if round<rounds
      A(:,:,round+1)=GrowRandomGraph(A(:,:,round+1),degree,corrupt,sybil);
    end

    if(mod(round,10)==0)
%    figure(1,'name','mint sum')
%    bar(sum(mintHistory));
%    ylim([0,rounds]);
%    drawnow;
%    figure(2,'name','mint')
%    plot(shifter + mintHistory);
%    figure(3,'name','dead')
%    plot(shifter + dead);
      figure(f4)
      plot(shifter + inDebt);
      drawnow
    end  
  end
end
