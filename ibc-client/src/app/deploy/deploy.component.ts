import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-deploy',
  templateUrl: './deploy.component.html',
  styleUrls: ['./deploy.component.css']
})
export class DeployComponent implements OnInit {

	compInfo: string = "Loading...";

  constructor() {
    this.compInfo = "no contract selected yet"}

  ngOnInit(): void {
  }

	fileChanged($event):void {
		console.log("app-deploy.fileChanged");
		const file = (<HTMLInputElement>document.getElementById("file")).files[0];
		var fileReader = new FileReader();
		fileReader.readAsText(file);
		fileReader.onload = function(e) {
			console.log("fileReader.onload");
//			this.compInfo = "FileReader works!";
		}
	}
}
