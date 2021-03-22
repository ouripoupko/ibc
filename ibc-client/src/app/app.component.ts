import { Component, OnInit } from '@angular/core';
import { ContractService } from './contract.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {

  names: string[];
  agent: string;
  newAgent: string;
  title ='The Identity BlockChain';

  getIdentities(): void {
    this.contractService.getIdentities()
      .subscribe(names => this.names = names);
  }

  constructor(
    private router: Router,
    private contractService: ContractService) { }

  ngOnInit(): void {
    this.getIdentities();
  }

  onSelect(): void {
    this.router.navigate([this.agent,'contracts']);
  }

  onAddAgent(): void {
    console.log('try');
    if(this.newAgent) {
      console.log('will do');
      this.contractService.setIdentity(this.newAgent)
        .subscribe(names => this.names = names);
    }
  }
}
