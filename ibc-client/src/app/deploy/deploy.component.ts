import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common'

import { ContractService } from '../contract.service';
import { Contract } from '../contract';

@Component({
  selector: 'app-deploy',
  templateUrl: './deploy.component.html',
  styleUrls: ['./deploy.component.css']
})
export class DeployComponent implements OnInit {

  agent: string;
	compInfo: string = "Loading...";
	fileFound: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private location: Location,
    private contractService: ContractService
  ) {
    this.compInfo = "no contract selected yet"
  }

  ngOnInit(): void {
    this.agent = this.route.snapshot.paramMap.get('agent');
  }

	fileChanged($event):void {
		console.log("app-deploy.fileChanged");
		const file = (<HTMLInputElement>document.getElementById("file")).files[0];
		var fileReader = new FileReader();
		fileReader.readAsText(file);
		fileReader.onload = function(e) {
			console.log("fileReader.onload");
			this.compInfo = e.target.result;
			this.fileFound = true;
		}.bind(this);
	}

  deploy(name: string): void {
    name = name.trim();
    if (!name) { return; }
    if (!this.fileFound) { return; }

    let contract: Contract = {} as Contract;
    contract.code = this.compInfo;
    contract.address = window.location.href.replace(window.location.pathname,'/');
    contract.pid = this.agent;

    this.contractService.addContract(this.agent, name, contract)
      .subscribe();
    this.compInfo = "no contract selected yet"
		this.fileFound = false;
  }

}
