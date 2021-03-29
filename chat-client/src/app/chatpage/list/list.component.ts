import { Component, OnInit, Input, OnChanges } from '@angular/core';
import { Collection } from '../../statement';
import { Method } from '../../contract';
import { FormControl } from '@angular/forms';
import { ContractService } from '../../contract.service';
import {CdkDragDrop, moveItemInArray} from '@angular/cdk/drag-drop';

@Component({
  selector: 'app-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.css']
})
export class ListComponent implements OnInit, OnChanges {

  @Input() sid: string;
  kids: Collection = {};
  order: string[] = [];
  statementForm: FormControl = new FormControl();
  @Input() version: number;

  constructor( private contractService: ContractService ) { }

  ngOnInit(): void {
  }

  ngOnChanges(): void {
    this.getStatements();
  }

  submit() {
    this.createStatement(this.statementForm.value);
    this.statementForm.setValue("");
  }

  createStatement(statement): void {
    const method = this.sid ? { name: 'reply', values: [this.sid, statement, 'not now please']} as Method :
                                        { name: 'create_topic', values: [statement]} as Method;
    this.contractService.createStatement(method)
      .subscribe();
  }

  getStatements(): void {
    this.contractService.getStatements({ name: 'get_kids', values: [this.sid]} as Method)
      .subscribe(collection => {
        Object.entries(collection).forEach(
          ([sid, statement]) => {
            let stored = null;
            if(sid in this.kids) {
              stored = this.kids[sid];
            }
            if(stored) {
              if(stored.version != statement.version) {
              }
              if(stored.kids_version != statement.kids_version) {
                stored.kids_version = statement.kids_version
              }
            } else {
              this.kids[sid] = statement;
              this.order.push(sid);
            }
          }
        );
      });
  }

  drop(event: CdkDragDrop<string[]>) {
    moveItemInArray(this.order, event.previousIndex, event.currentIndex);
  }
}
