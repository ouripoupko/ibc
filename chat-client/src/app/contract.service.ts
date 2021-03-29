import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract, Method } from './contract';
import { Collection } from './statement';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private url: string;
  private identity: string;
  private contract: string;

  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient) { }

  getUrl() {
    return this.url;
  }

  getIdentities(server: string): Observable<string[]> {
    this.url = server;
    return this.http.get<string[]>(`${this.url}ibc/app`).pipe(
        tap(_ => console.log('fetched identities')),
        catchError(this.handleError<string[]>('getIdentities', []))
      );
  }

  getContracts(identity: string): Observable<Contract[]> {
    this.identity = identity;
    return this.http.get<Contract[]>(`${this.url}ibc/app/${this.identity}`).pipe(
        tap(_ => console.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  setContract(contract: string) {
    this.contract = contract;
  }


  listen(): EventSource {
    return new EventSource(`${this.url}stream/${this.identity}/${this.contract}`);
  }

  getStatements(method: Method): Observable<Collection> {
    const url = `${this.url}ibc/app/${this.identity}/${this.contract}/${method.name}`;
    return this.http.post<Collection>(url, method, this.httpOptions).pipe(
//      tap((list: Collection) => console.log(list)),
      catchError(this.handleError<Collection>(`getContract name=${name}`))
    );
  }

  createStatement(method: Method): Observable<any> {
    const url = `${this.url}ibc/app/${this.identity}/${this.contract}/${method.name}`;
    return this.http.put<any>(url, method, this.httpOptions).pipe(
      tap(_ => console.log('created statement')),
      catchError(this.handleError<any>(`createStatement name=${name}`))
    );
  }

  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }

}
